## Why

As dotações de Mossoró-RN, Juazeiro-BA e Itabirito-MG foram importadas (45 fatos da aba DOTAÇÃO),
mas a DRE real roda com Orçado = 0 porque faltam regras: sinal dos valores, mês de cada valor (a
dotação é anual/por prazo e o TON não divide por 12 sem regra), qual linha da dotação casa com qual
natureza da DRE, e o que fazer com unidades sem dotação. O relatório de junho já apontava 6 de 7
unidades com dotação desatualizada (contexto 03 §4.7). Sem orçado comparável não existe controle de
desvio orçado × realizado — opção B da priorização da reunião.

## What Changes

- Decisões versionadas para cada dotação: sinal, calendário (mensal explícito, por prazo ou por
  cronograma da própria planilha), e mapeamento linha da dotação → linha da DRE (candidato só por
  código exato ou aprovação anterior).
- Política de entradas `ACTUAL_AND_APPROVED_BUDGET` habilitada por unidade quando a dotação estiver
  aprovada; unidades sem dotação aparecem "sem orçado", nunca com zero silencioso.
- DRE com Orçado, Realizado, variação absoluta e % (variação % nula quando orçado = 0).
- Sinal de dotação desatualizada: data-base da dotação anterior ao último reajuste/CCT conhecido ou
  mais antiga que o limite aprovado pela Controladoria.

## Capabilities

### New Capabilities
- `budget-vs-actual`: orçado × realizado a partir das dotações aprovadas.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/financial_readiness.py` (decisões de período/sinal/mapeamento de dotação),
  `financial_domain.py`, motor/UI da DRE.

## Dependências

- Respostas O1–O3 da Luyla (vigência das dotações, mensal × anual, sinal, casamento com natureza).
  Depende de `carry-over-decisions-on-reimport` (política de entradas).

## Estado de dado

Real (três dotações).

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

A própria Controladoria ainda não fez a compatibilização dotação → natureza (também não está no
Power BI), e só Mossoró, Juazeiro-BA e Itabirito têm dotação 2026; a licitação está atualizando as
demais. **Esta change fica para depois** de a Controladoria definir a compatibilização.
