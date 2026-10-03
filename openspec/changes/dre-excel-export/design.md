## Context

O motor de DRE já produz `DreCalculationRun` + `DreResultLine` com proveniência e expõe
contribuintes por linha (`/calculations/{run_id}/lines/{line_code}/contributors`). O CSV atual
serializa só valores. O cliente quer rastrear o cálculo dentro do Excel.

## Goals / Non-Goals

**Goals:** planilha auditável com fórmulas; números idênticos ao cálculo persistido; origem de cada
fato; reproduzível (mesmo run → mesmo arquivo, exceto data de geração).

**Non-Goals:** editar a DRE no Excel e reimportar; macros/VBA; substituir o BI em painéis.

## Decisions

- **Um arquivo por ano até o mês escolhido.** O botão parte do resultado oficial na tela
  (`run_id`) e o arquivo cobre jan até o mês desse resultado, na mesma base e versão de estrutura,
  com um bloco consolidado (só para quem lê o consolidado) e um bloco por unidade/filial visível.
  Responde à pergunta aberta do contador com "colunas por mês num arquivo anual"; revisar com ele.
- **Fórmulas sobre aba Base em vez de valores.** A aba Base é uma tabela do Excel chamada `Base`.
  Cada linha folha usa `SUMIFS(Base[Valor], Base[Linha DRE], código, Base[Competência], mês
  [, Base[Unidade], unidade])`; linhas de total usam as fórmulas declarativas da estrutura
  traduzidas para referências de célula (SUM_CHILDREN/SUM_LINES → soma, SUBTRACT → diferença,
  RATIO → `IF(den=0,"",num/den*100)`); o Acumulado soma os meses nas folhas e repete a fórmula
  nos totais. A Luyla pode acrescentar linhas na tabela e as fórmulas acompanham.
- **Valores em cache gravados junto com a fórmula** (XlsxWriter, já instalado via python-pptx,
  agora dependência direta; openpyxl não grava cache). O cache vem do mesmo avaliador do motor
  (`evaluate_lines`) aplicado à Base.
- **Conferência obrigatória antes de servir.** O repositório compara cada valor da planilha com
  as linhas persistidas de todo resultado READY incluído (mês e acumulado) ao centavo; se diferir,
  responde conflito e não entrega arquivo.
- **Base = fatos ACTUAL da normalização** mapeados (APPROVED) para linhas-fonte da versão, com
  join externo de unidade para que fatos sem unidade entrem no consolidado.
- **Aba Premissas em vez de "Tratamentos e decisões" e "Pendências".** Pedido de 2026-10-03:
  uma aba com o que ainda não está aplicado (parcelamentos, PIS/COFINS, receita, orçado zerado,
  unidades sem DRE pronta, lançamentos sem unidade) e o cabeçalho da base.
- **Base NOT_READY:** exportação bloqueada (conflito). Meses de unidade sem DRE pronta aparecem
  em cinza, marcados "Não pronta", e listados na Premissas. O rascunho para Controladoria fica
  para quando houver pedido.
- **Texto do NG nunca vira fórmula:** `strings_to_formulas` e `strings_to_urls` desligados.

## Risks / Trade-offs

- [Planilhas grandes (6k+ linhas por semestre) com SUMIFS ficam lentas] → tabela estruturada e
  uma aba Base por arquivo; medir com jan–jun/2026.
- [Fórmula de total divergente da estrutura] → teste gera a planilha, recalcula e compara com o run.
- [Código de unidade numérico ("000001") como critério do SUMIFS] → o Excel compara pelo valor;
  os códigos atuais são distintos como número. Conferido no Excel com a base real.
- Medido com jan–jun/2026 real: 6.307 lançamentos, 677 KB, 2,3 s no servidor, recálculo completo
  no Excel em ~19 s.

## Open Questions

- O contador prefere colunas por mês num único arquivo anual ou um arquivo por competência?
