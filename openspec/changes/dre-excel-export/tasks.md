## 1. Exportação

- [ ] 1.1 Módulo de exportação XLSX (openpyxl) a partir de `DreCalculationRun` e contribuintes
- [ ] 1.2 Aba Base como tabela estruturada com proveniência completa
- [ ] 1.3 Tradução das fórmulas declarativas da estrutura para fórmulas de célula; valores em cache
- [ ] 1.4 Abas Tratamentos e decisões e Pendências; cabeçalho com base, importação e versão
- [ ] 1.5 Regra NOT_READY: bloqueio ou rascunho com marca

## 2. API e UI

- [ ] 2.1 `GET /api/ton/dre/calculations/{run_id}/export.xlsx` com ACL de escopo
- [ ] 2.2 Botão "Baixar Excel" na DRE (mensal e acumulado) com estados de carregamento e erro

## 3. Validação

- [ ] 3.1 Teste: gerar, recalcular (LibreOffice headless quando disponível) e comparar com o run ao centavo
- [ ] 3.2 Medir tamanho/tempo com jan–jun/2026 consolidado
- [ ] 3.3 Abrir no Excel e conferir com a Luyla/contador; registrar ajustes de layout pedidos
- [ ] 3.4 Atualizar `openspec/roadmap.md`
