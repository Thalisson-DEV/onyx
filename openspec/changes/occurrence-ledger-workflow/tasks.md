## 1. API

- [ ] 1.1 Endpoints de listagem/filtro do ledger com ACL por unidade/contrato/grupo
- [ ] 1.2 Atribuição (usuário ou cargo nominal), prazo padrão pela régua, notas, causa provável, ação recomendada
- [ ] 1.3 Transições de status com a máquina de estados existente; bloqueio de encerramento automático de 🔴
- [ ] 1.4 Contador de ciclos em aberto no fechamento
- [ ] 1.5 Exportação Excel do ledger filtrado

## 2. UI

- [ ] 2.1 `OccurrencesPage` com tabela, filtros e detalhe (evidência, impacto, histórico de eventos)
- [ ] 2.2 Diálogos de atribuição e transição com justificativa e confirmação
- [ ] 2.3 Fila de trabalho e sino com dono/prazo reais; "Perguntar ao TON sobre este item"

## 3. Validação

- [ ] 3.1 Testes de API e de máquina de estados; jest da página
- [ ] 3.2 Chrome com usuário Controladoria (sem admin)
- [ ] 3.3 Atualizar `specs/occurrence-ledger` ao arquivar e `openspec/roadmap.md`
