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

## Atualização da reunião de 2026-10-23

- **Custos fixos como referência mensal:** a Luyla terminou a planilha de custos fixos da Administração
  Central (`Custos Fixos - Administracao Central.xlsm` e o diagnóstico na pasta compartilhada). Ela é
  o valor de referência do que se deve gastar por mês (energia, folha etc.), a "meta". Em 2027 a
  Controladoria compara essa referência com a DRE da matriz. Isso pode vir antes das dotações: um
  orçado da matriz por conta/natureza, mês a mês, versionado.
- **Dotações:** as que estão na pasta (pasta "Dotações - João Hebert (set-26)", por unidade) são as que
  participam da licitação e não necessariamente a referência de comparação. A Controladoria ainda vai
  mudar o formato para aplicar na DRE e ver se o realizado está na média projetada ("futuro não muito
  distante"). Esperar o novo formato.
- **Metas de faturamento por contrato** até o fim do ano e avaliação de se a taxa de administração de
  2% de cada contrato basta para a administração central (ata da Controladoria de 16/10): entram aqui
  como orçado por contrato quando a Controladoria definir as metas.
