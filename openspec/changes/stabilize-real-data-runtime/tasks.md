## 1. Runtime reprodutível

- [ ] 1.1 Fazer backup do banco local (`pg_dump` para `Documents/onyx_backups/`)
- [ ] 1.2 Normalizar `*.sh` para LF e reconstruir `onyx-backend` com a stack parada
- [ ] 1.3 Reconstruir `onyx-web-server` com a stack parada (memória WSL)
- [ ] 1.4 Subir os contêineres um a um e confirmar saúde; registrar o procedimento em `plans/ton/local-runtime.md`
- [ ] 1.5 Confirmar que nenhuma alteração depende de `docker cp` (comparar código da imagem com `main`)

## 2. Assistente

- [ ] 2.1 Corrigir `financial_context` para buscar os cálculos do período/escopo pedido na base mais recente (sem limite fixo de 10)
- [ ] 2.2 Medir latência e número de chamadas das perguntas de referência na base real
- [ ] 2.3 Reduzir etapas: ferramenta agregada de fechamento por período/escopo, instrução de parada no prompt
- [ ] 2.4 Criar suíte de grounding (perguntas de referência × read models) e rodá-la no CI local
- [ ] 2.5 Validar no Chrome três perguntas reais e registrar tempo e números

## 3. Produto e fontes

- [ ] 3.1 Derivar o texto dos cards de especialistas do resultado persistido (CFO não nega DRE calculada)
- [ ] 3.2 Identidade de dotação declarada (unidade + data-base) e rejeição por hash duplicado; migração dos três registros existentes sem perder histórico
- [ ] 3.3 Criar usuário Controladoria sem admin e percorrer todas as superfícies; corrigir mensagens de permissão
- [ ] 3.4 Arquivar conversas de teste da preparação (sem apagar auditoria)

## 4. Fechamento

- [ ] 4.1 Testes backend focados + jest TON + tsc + lint
- [ ] 4.2 Atualizar `openspec/roadmap.md` e `plans/ton/context/08_REAL_VS_SYNTHETIC_AND_EXTERNAL_DEPENDENCIES.md`

## 5. Ajustes pedidos na reunião de 2026-10-03

- [ ] 5.1 Renomear o filtro "Escopo" da DRE para "Unidades/filiais"
- [ ] 5.2 Renomear o especialista PROCUREMENT para "Compras/Suprimentos" em toda a UI
