## Context

O motor de DRE já produz `DreCalculationRun` + `DreResultLine` com proveniência e expõe
contribuintes por linha (`/calculations/{run_id}/lines/{line_code}/contributors`). O CSV atual
serializa só valores. O cliente quer rastrear o cálculo dentro do Excel.

## Goals / Non-Goals

**Goals:** planilha auditável com fórmulas; números idênticos ao cálculo persistido; origem de cada
fato; reproduzível (mesmo run → mesmo arquivo, exceto data de geração).

**Non-Goals:** editar a DRE no Excel e reimportar; macros/VBA; substituir o BI em painéis.

## Decisions

- **Fórmulas sobre aba Base em vez de valores.** Cada linha folha usa `SUMIFS(Base[Valor],
  Base[Linha DRE], código, Base[Competência], mês)`; linhas de total usam as fórmulas declarativas da
  estrutura traduzidas para referências de célula. Alternativa rejeitada: valores + comentário de
  origem (não é memória de cálculo).
- **Valores em cache gravados junto com a fórmula** para que visualizadores sem recálculo mostrem o
  número certo; teste compara cache × cálculo persistido × recálculo (LibreOffice headless no teste
  de integração, quando disponível).
- **openpyxl** (já dependência do parser) — sem nova biblioteca.
- **Base NOT_READY:** exportação bloqueada por padrão; com permissão de Controladoria, exportação
  "rascunho" com marca d'água textual em todas as abas e aba Pendências preenchida.

## Risks / Trade-offs

- [Planilhas grandes (6k+ linhas por semestre) com SUMIFS ficam lentas] → tabela estruturada e
  uma aba Base por arquivo; medir com jan–jun/2026.
- [Fórmula de total divergente da estrutura] → teste gera a planilha, recalcula e compara com o run.

## Open Questions

- O contador prefere colunas por mês num único arquivo anual ou um arquivo por competência?
