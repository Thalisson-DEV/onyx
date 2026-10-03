## Why

Sem histórico o TON não compara com o ano anterior, não vê sazonalidade, não roda previsão (§17
exige no mínimo 6 competências fechadas) e não sabe dizer se algo está fora do normal. Hoje só
jan–jun/2026 existe. Atenção: T2 (média móvel de 3 meses) e T5 (receita replicada) **já** têm dado
suficiente em 2026 a partir de abril; o histórico 2025 amplia a janela, habilita comparação anual e
sazonalidade e dá base para o modo previsão.

## What Changes

- Importar NG 2025 (e faturamento 2025, se disponível) pelo mesmo pipeline, por competência.
- Tratar a mudança de plano de contas/naturezas entre anos como decisão versionada (mapeamento por
  vigência), nunca por similaridade.
- DRE 2025 mensal e comparação 2026 × 2025 (mesmo mês, acumulado) para unidades com cobertura nos
  dois anos.
- Indicador de cobertura histórica por unidade (meses fechados disponíveis), usado pelas regras e pelo
  modo previsão para decidir se podem rodar.

## Capabilities

### New Capabilities
- `financial-history`: base histórica multi-ano, comparação anual e cobertura por unidade.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Pipeline existente (fontes, revisão, normalização, DRE) com períodos de 2025; mapeamentos com
  vigência; DRE UI (comparação), ferramentas do assistente.

## Dependências

- Pergunta à Luyla: o fechamento 2025 "ok" existe e está autorizado? Quais meses? Mesmo layout de
  export? Pode vir da integração direta com o NG (change `ng-direct-integration`).

## Estado de dado

Real, quando fornecido.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

A Luyla pediu a comparação com o mesmo período do ano anterior por unidade (ex.: custo de folha no fim
de ano). Ela prefere que 2025 venha pela integração com o NG, sem tratamento manual. A comparação na
DRE já está preparada no produto, só falta o dado.
