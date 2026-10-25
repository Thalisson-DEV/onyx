## Why

Veículos/equipamentos são ~37% da composição de custo de Mossoró (§4.1) e combustível é uma das
maiores despesas da Vale Norte; o relatório de junho aponta falta de controle consolidado de postos
conveniados, desconto, prazo, limite e consumo por veículo (contexto 03 §4.8), e a DRE de Mossoró
mar–abr/2026 mostrou combustível de R$ 11 mil e R$ 22 mil contra média de R$ 362 mil (recargas fora da
competência). O especialista **TON FROTA** está "aguardando fonte" e a rotina **R2 — Auditoria de
combustível** (semanal, sexta 07h) está bloqueada.

## What Changes

- Fontes **frota** (placa, tipo, unidade, contrato, situação, km/horímetro, CRLV, seguro, capacidade do
  tanque), **abastecimento** (placa, data, hora, litros, valor, odômetro, posto, motorista) e
  **manutenção** (placa, data, tipo, causa, valor, fornecedor), conformes ao contrato de dados (§3.1).
- Testes **T21** consumo anômalo (km/l × média do mesmo tipo na mesma unidade, mínimo 3 comparáveis,
  > 15% por 2 semanas), **T22** abastecimento inconsistente (mesma placa < 4h, litros > tanque,
  odômetro regressivo, abastecimento sem produção no dia), **T23** manutenção acumulada > 60%/80% do
  valor de reposição, **T24** frota licitada (dotação) × frota em operação.
- Rotina **R2** semanal; TON FROTA ativo com ferramentas próprias; decisão
  consertar/reformar/substituir/locar como recomendação (§15).
- Cadastro de postos conveniados (desconto, prazo, limite) e compra fora de posto conveniado.

## Capabilities

### New Capabilities
- `fleet-domain`: fontes de frota/abastecimento/manutenção, T21–T24, R2 e TON FROTA.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novos perfis e fatos de domínio, testes, rotina R2, especialista FROTA, superfície de frota.

## Dependências

- Fontes de frota/abastecimento/manutenção por unidade (qual sistema/planilha? quem mantém?), valor de
  reposição por tipo (T23), dotação confirmada (T24), produção diária (parte do T22).

## Estado de dado

Real, quando fornecido.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

A frota hoje é uma planilha mantida por uma pessoa (Igor). A Luyla concordou que o melhor é **lançar a
frota direto no TON, em tempo real**, em vez de importar a planilha. Acrescentar a esta change um
cadastro de frota no TON (veículo, tipo, unidade, contrato, situação, km/horímetro, documentos) com
permissão de edição para o responsável; a planilha atual serve para modelar os campos e fazer a carga
inicial.

## Atualização da reunião e da análise de 2026-10-23

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`. Padrão proposto à Controladoria: documento
"TON — Padrão de informações das unidades" (Claude Docs, enviado à Luyla em 2026-10-23).

**O que a Luyla disse:**
- O controle de frota e combustível é "muito manual, muitas pessoas ao mesmo tempo e várias planilhas
  de Excel soltas". Os números das unidades e do financeiro não batem. O Igor (engenheiro mecânico,
  frota) também controla. Qualquer um altera nome e valor na planilha sem deixar histórico.
- Combustível: cada unidade controla de um jeito. Só Mossoró usa cartão (Alelo), com extrato por
  veículo; nas outras há guia de autorização por escrito, comunicado ou "folhinha". Muitas vezes
  ninguém autoriza: a pessoa vai e abastece, às vezes em outro carro. A variação não tem explicação
  (Juazeiro do Norte: maio ~R$ 100 mil, junho ~R$ 326 mil). Ela pesquisa um **cartão único** para
  todas as unidades, aceito em qualquer posto, com controle por placa e por pessoa e limite de valor,
  e quer o extrato integrado ao TON. Vai mandar o nome da empresa.
- Locações: Vamos (locadora; R$ 618 mil/mês, 41 itens) e locações diretas de empresas parceiras,
  proprietários e funcionários. Quando um veículo para, quebra, muda de unidade ou deixa de ser
  necessário, o gestor avisa a diretoria operacional, que avisa o Igor, que avisa o financeiro. A
  informação se perde e a empresa continua pagando. Ela quer um **fluxo oficial**: registro no
  sistema, aviso em tempo real à Controladoria e à Diretoria, regras do que precisa ser avisado na
  hora (mudança, transferência, quebra de contrato, veículo parado por manutenção que cabe ao locador)
  e treinamento.
- Frota e locações vão direto no TON, não no Zeev (mais flexível, com foto e contrato anexados).

**O que os arquivos mostram (pasta compartilhada, 21–22/10):**
- `Gerenciamento de Frota 07.07.2026.xlsx` já é um bom cadastro-base: prefixo interno (CCL0xx),
  placa, equipamento, condição (próprio/locado/leasing/agregado), unidade, status (operativo,
  inoperante, devolvido, vendido, sinistro), serviço, chegada/saída, combustível, medidor
  (hodômetro/horímetro), chassi, Renavam, proprietário com CNPJ e valor mensal. São 118 operativos e
  81 inativos. Serve de carga inicial.
- A planilha da Vamos avisa: "pode não estar batendo com a unidade, pois alguns são transferidos
  entre unidades e não recebemos essa informação". A mesma placa aparece em unidades diferentes.
- Veículos da diretoria, de outras empresas do grupo (Delta Park, Shopping, Guarulhos) e de uso
  pessoal aparecem na frota e são abastecidos na matriz. O rateio entre empresas está a definir.
- Relatório do posto da matriz: motorista em texto livre com grafias diferentes, KM 0/1/22/5000/888888,
  placa digitada de várias formas, lubrificante e acessório junto com o combustível.
- Extrato Alelo (fatura de agosto, consumo de 29/06 a 23/07, R$ 146 mil):
  - nenhuma linha tem motorista, e o hodômetro vem quase sempre zerado;
  - um cartão de compactador fez 25 abastecimentos (~2.580 L) em duas horas;
  - seis cartões passaram exatamente R$ 15.000 (2.057 L) cada no mesmo dia, um deles cadastrado como
    carro; os valores redondos somam ~R$ 112 mil da fatura;
  - veículos leves aparecem com volume maior que o tanque (um deles é locado).
  Pode haver explicação (tanque, galão, crédito no posto), mas o extrato não mostra o consumo por
  veículo. A pergunta foi levada à Luyla no documento.
- `COMBUSTIVEL FILIAIS jan a set.xlsx` não serve como fonte. Mossoró aparece zerado em 7 de 9 meses,
  porque a fatura Alelo vence 45 a 60 dias depois do consumo. Juazeiro BA aparece zerado o ano todo,
  embora a unidade lance ~R$ 22 mil por quinzena no posto.
- Locações em Sento Sé descontam o combustível do aluguel. Há locação "sem contrato" em Mossoró e
  pagamentos de locação por PIX para CPF diferente do locador.

**O que muda nesta change:**
- **Cadastro único de veículo/equipamento** no TON, com capacidade do tanque e medidor obrigatórios. Ele
  substitui a planilha do Igor e a da Vamos como referência de unidade.
- **Contrato de locação** como cadastro: locador (do cadastro de fornecedores), veículos, valor e forma
  de cálculo, quem paga o combustível, início, fim, aviso prévio e contrato anexado. Sem anexo, a
  locação fica marcada como "sem contrato". As locações saem de `procurement-domain` e ficam aqui.
- **Eventos de frota** registrados pelo gestor uma vez, com aviso simultâneo a frota, diretoria
  operacional, financeiro e Controladoria: entrada, transferência, quebra/parada, volta à operação,
  devolução/encerramento, troca de veículo pelo locador, sinistro/multa e venda.
- **Regras de locação:**
  - só se paga locação com contrato ativo (o aluguel do mês é gerado pelo contrato);
  - antes do pagamento, o gestor confirma todo mês os veículos em uso (substitui a declaração que a
    planilha de Mossoró já tem);
  - dias parados geram desconto quando o contrato prevê;
  - o custo é rateado por unidade e por dias (Vamos e demais);
  - locação de funcionário tem contrato e pagamento na conta do dono do veículo;
  - o abastecimento de veículo locado segue o contrato.
- **Registro de abastecimento** com motorista (CPF), data e hora, litros, combustível, preço,
  hodômetro/horímetro real, posto (CNPJ), competência pela data do abastecimento e marcação de
  abastecimento fora do veículo (tanque, galão) com motivo. Fontes: extrato do cartão (Alelo hoje,
  cartão único depois), relatório do posto, guia manual.
- **Solicitação de abastecimento com aprovação** como opção, a decidir com a Luyla (modelo do CES: a
  equipe solicita com foto do painel, o gestor aprova ou reduz, o financeiro libera).
- **Conferências novas**, além de T21–T24:
  - abastecimento sem motorista ou sem hodômetro válido;
  - sequência impossível no mesmo cartão (volume acima do tanque num intervalo curto);
  - valores redondos repetidos;
  - veículo inativo ou devolvido abastecido ou pago;
  - locação sem contrato ou vencendo;
  - evento registrado com atraso (dias entre o fato e o registro).
- **Competência do combustível:** a DRE recebe o consumo no mês do abastecimento, não no vencimento da
  fatura (ata de 20/10).

## Dependências (acrescentadas em 2026-10-23)

- Nome e API da empresa do cartão único (Luyla); extratos Alelo de jan a set (Cláudia, ata de 20/10).
- Explicação da Luyla sobre os abastecimentos de 29/06 no extrato Alelo.
- Fluxo oficial e regras de aviso definidos com a Controladoria e a Diretoria; treinamento dos gestores.
- Quem paga o combustível de veículo locado, contrato a contrato.
- Rateio dos veículos de outras empresas do grupo e de uso pessoal.
- Pergunta em aberto: controlar também a documentação de quem dirige (CNH e validade)?
