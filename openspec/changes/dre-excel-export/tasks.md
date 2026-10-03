## 1. Exportação

- [x] 1.1 Módulo de exportação XLSX (XlsxWriter, para gravar valores em cache) a partir de `DreCalculationRun` e dos fatos contribuintes
- [x] 1.2 Aba Base como tabela estruturada com proveniência completa
- [x] 1.3 Tradução das fórmulas declarativas da estrutura para fórmulas de célula; valores em cache
- [x] 1.4 Aba Premissas (substitui Tratamentos e decisões e Pendências, pedido de 2026-10-03); cabeçalho com período, importação, estrutura, nº de lançamentos e data de geração
- [x] 1.5 Regra NOT_READY: bloqueio do resultado não pronto; meses de unidade sem DRE pronta marcados "Não pronta" e listados na Premissas (rascunho para Controladoria: só se pedido)

## 2. API e UI

- [x] 2.1 `GET /api/ton/dre/calculations/{run_id}/export.xlsx` com ACL de escopo
- [x] 2.2 Botão "Baixar Excel" na DRE (mensal e acumulado) com estados de carregamento e erro

## 3. Validação

- [x] 3.1 Teste: gerar, recalcular e comparar com o run ao centavo (teste unitário com avaliador das fórmulas; teste com banco sintético; recálculo no Excel real via COM: 5.544 fórmulas, 0 divergências)
- [x] 3.2 Medir tamanho/tempo com jan–jun/2026: 6.307 lançamentos, 24 blocos, 677 KB, 2,3 s no servidor, 19 s para o Excel recalcular tudo; 3.597 valores conferidos com a DRE persistida, 0 diferenças
- [ ] 3.3 Abrir no Excel e conferir com a Luyla/contador; registrar ajustes de layout pedidos
- [x] 3.4 Atualizar `openspec/roadmap.md`
- [ ] 3.5 Validar no Chrome: baixar o Excel na tela da DRE e conferir os totais de jan–jun com a tela
