## Why

O sucesso do TON "é medido em uma única unidade: quanto dinheiro ajuda a economizar, recuperar,
proteger ou gerar — registrado, com dono, prazo e verificação posterior" (Prompt Mestre §1). Isso
exige o **ledger de oportunidades** (§13.2), o **painel Dinheiro Escondido** (§14.4, tabela por impacto
mensal decrescente com total identificado e parcela verificada) publicado pela rotina **R5** (mensal
D+4, Gerência Geral), e o **registro de ROI da inteligência** (§13.3: economia identificada, receita
recuperada, custo evitado, custo do sistema, ROI líquido), com a regra: só é realizada a economia
verificada contra a base do mês seguinte. O modelo já distingue `ledger_kind = OPPORTUNITY` e impacto
previsto × realizado, mas nada consolida.

## What Changes

- Ledger de oportunidades (ocorrências OPPORTUNITY e impactos das EXCEPTION com categoria de ganho),
  com campos do §13.2.
- Painel Dinheiro Escondido (tela + seção de relatório) ordenado por impacto mensal, com total
  identificado e verificado.
- R5 mensal D+4 para a Gerência Geral.
- Registro de ROI do exercício: identificado, recuperado, evitado, custo do sistema (informado pela
  gestão), ROI líquido; previsto e realizado separados; confiança Baixa fora dos totais.

## Capabilities

### New Capabilities
- `hidden-money`: ledger de oportunidades, painel Dinheiro Escondido, R5 e ROI.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Read models sobre `OccurrenceImpact`, nova tela, rotina R5, relatórios executivos.

## Dependências

- `impact-quantification`, `action-verification` (realizado), `occurrence-ledger-workflow`,
  `routine-framework`. Custo do sistema informado pela gestão.

## Estado de dado

Real; só ganha números depois que regras quantificadas e verificações existirem.
