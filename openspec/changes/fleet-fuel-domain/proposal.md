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
