## 1. Runtime reprodutível

- [x] 1.1 Fazer backup do banco local (`pg_dump` para `Documents/onyx_backups/`) — 2026-10-05: `Documents/onyx-backups/onyx-postgres-20261005-2032-before-email-flows.dump` (pg_dump -Fc, em `c4f2a9e6b1d3`)
- [x] 1.2 Normalizar `*.sh` para LF e reconstruir `onyx-backend` com a stack parada — 2026-10-05, imagem da `main` `b2d5d0dc37`; anteriores marcadas `:backup-before-email-flows`
- [x] 1.3 Reconstruir `onyx-web-server` com a stack parada (memória WSL) — 2026-10-05
- [x] 1.4 Subir os contêineres um a um e confirmar saúde; registrar o procedimento em `plans/ton/local-runtime.md` — 10 contêineres no ar em 2026-10-05 (db, cache, opensearch, model servers, code-interpreter, api_server, background, web, nginx); procedimento em `plans/ton/local-runtime.md` §8
- [x] 1.5 Confirmar que nenhuma alteração depende de `docker cp` (comparar código da imagem com `main`) — imagens construídas da `main`; o api_server aplicou `d7a1e4c9b2f6` e `e5b8c2d4f1a7` ao subir

## 2. Assistente

- [x] 2.1 Corrigir `financial_context` para buscar os cálculos do período/escopo pedido na base mais recente (sem limite fixo de 10) — base real: 29 resultados na base mais recente (antes 10), 0,09 s
- [x] 2.2 Medir latência e número de chamadas das perguntas de referência na base real — antes: 1,5–3 min; com a ferramenta agregada: 1 chamada, mas ~53 s numa resposta de 490 palavras (geração de texto). Prompt limitado a ~200 palavras e tabela com as linhas principais
- [x] 2.3 Reduzir etapas: ferramenta agregada de fechamento por período/escopo, instrução de parada no prompt — `ton_get_closing_overview`; base real: 0,05–1,0 s, linhas iguais ao demonstrativo (jun consolidado e abr MOSSORÓ-RN); "Juazeiro" ambíguo devolve candidatas
- [x] 2.4 Criar suíte de grounding (perguntas de referência × read models) e rodá-la no CI local — `backend/scripts/ton_grounding_suite.py` + `onyx/ton/agent/grounding.py` (testes unitários)
- [x] 2.5 Validar no Chrome três perguntas reais e registrar tempo e números — 2026-10-04, base real, stream medido do envio ao fim: fechamento de junho 18,0 s (14/14 valores = demonstrativo); resultado de abril em Mossoró-RN 14,2 s (8/8); pendências que impedem a DRE 16,9 s (6/6). 1 chamada (`Fechamento do período`) em cada; primeira palavra em 8,5–10,8 s

## 3. Produto e fontes

- [ ] 3.1 Derivar o texto dos cards de especialistas do resultado persistido (CFO não nega DRE calculada)
- [ ] 3.2 Identidade de dotação declarada (unidade + data-base) e rejeição por hash duplicado; migração dos três registros existentes sem perder histórico
- [ ] 3.3 Criar usuário Controladoria sem admin e percorrer todas as superfícies; corrigir mensagens de permissão
- [ ] 3.4 Arquivar conversas de teste da preparação (sem apagar auditoria)

## 4. Fechamento

- [ ] 4.1 Testes backend focados + jest TON + tsc + lint
- [ ] 4.2 Atualizar `openspec/roadmap.md` e `plans/ton/context/08_REAL_VS_SYNTHETIC_AND_EXTERNAL_DEPENDENCIES.md`

## 5. Ajustes pedidos na reunião de 2026-10-03

- [x] 5.1 Renomear o filtro "Escopo" da DRE para "Unidades/filiais" (rótulo "Unidade/filial", seleção única)
- [x] 5.2 Renomear o especialista PROCUREMENT para "Compras/Suprimentos" em toda a UI
