Mapa completo: `capability-map.md`.

## Onda 1 — Fundação e pedido da Luyla

- [x] 1.1 Migração `f1a9c3e5b7d2`: `ton_agent_action`, `ton_dre_adjustment`; linha da estrutura com `source` (JSON da versão)
- [x] 1.2 Serviço `propose / apply / cancel / undo` por tipo de ação; cada proposta e decisão fica em `ton_agent_action` (quem propôs, quem aplicou, quando, resultado)
- [x] 1.3 Rotas `GET /ton/agent/actions?chat_session_id=`, `GET /ton/agent/actions/{id}`, `POST …/{apply|cancel|undo}`
- [x] 1.4 Motor da DRE: origens `BILLING` (campos da nota, emissão ou competência, sinal) e `ADJUSTMENT`; drill-down e Excel de cada uma
- [x] 1.5 Prévia da DRE em memória (antes × depois) para estrutura ou ajuste propostos
- [x] 1.6 Ferramentas: `ton_get_dre_structure`, `ton_propose_dre_structure_change`, `ton_propose_dre_adjustment`, `ton_propose_closing_treatment`, `ton_propose_dre_recalculation`
- [x] 1.7 Cartão de ação no chat (antes × depois, Aplicar, Cancelar, Desfazer) e mensagem de continuação
- [x] 1.8 Anexo no chat → `ton_propose_source_import` (arquivo pelo nome; prévia de reimportação; aplicar = importar, atualizar a base e recalcular)
- [x] 1.9 Prompt: quando propor, como descrever o efeito, nunca dizer "apliquei" antes do clique
- [ ] 1.10 Teste de integração: propor → aplicar → DRE com faturamento bruto e impostos → desfazer (validado à mão no navegador em 2026-10-21)

## Onda 2 — Investigar e decidir

- [x] 2.1 Investigação livre: `ton_search_entries`, `ton_supplier_summary`, `ton_compare_dre`, `ton_get_dre_line_entries`
- [x] 2.2 Testes do Prompt Mestre sob demanda: `ton_run_financial_test` T1, T2, T3, T4, T6, T8, T9, T10 (parâmetros explícitos, evidência por linha)
- [x] 2.3 Decisões com clique: classificação de contas, confirmação em lote, decisão de pendência, unidade de lançamentos sem unidade, ativar/pausar/rodar automação
- [x] 2.4 Filas: `ton_list_classification_queue`, `ton_list_unit_missing`, `ton_list_automations`
- [x] 2.5 Cartão de investigação (tabela enxuta, detalhes sob demanda)
- [ ] 2.6 Painel "O que o TON alterou nesta conversa"
- [ ] 2.7 Exportar o Excel da DRE pelo chat (link) e voltar versão da estrutura

## Onda 3 — Especialistas e memória

- [x] 3.1 Uma persona por especialista (`specialist_chat.py`): CFO, AUDITOR, CEO, COO, FROTA, RH, COMPRAS, CONTRATOS, COMPLIANCE, com foco, ferramentas e perguntas iniciais
- [x] 3.2 `sync_specialist_personas` no provisionamento e no tick das automações; rota `GET /ton/agent/specialists/{key}/configuration`
- [x] 3.3 `/ton/chat?foco=KEY` usa a persona do especialista; página Especialistas com "Conversar" para todos
- [x] 3.4 Regras da Controladoria: migração `a7d3f9b1c5e8`, `ton_propose_controller_rule`, `ton_get_controller_rules`, regras na leitura da estrutura
- [ ] 3.5 Barra de contexto mostra o especialista também depois que a conversa ganha `chatId`
- [ ] 3.6 Lista editável das regras numa tela

## Onda 4 — Ledger, proatividade e domínios

- [ ] 4.0 Impacto registrado (`OccurrenceImpact`) e verificação no ciclo seguinte (ROI)

- [x] 4.1 Registrar ocorrência a partir de um teste: regras DRAFT `TON-T1…T10`, o servidor roda o teste de novo e registra pelas chaves; repetição não duplica; criticidade PAD-CTRL sugerida e aprovada no clique (centro de custo sem receita mede no consolidado) — `db/ton/agent_ledger.py`
- [x] 4.2 Responsável, prazo e nota pela conversa (`ton_propose_occurrence_assignment`); impacto calculado vai no achado (`computed_impact_amount`)
- [x] 4.3 Varredura R1 diária é uma automação do motor (`ton-r1-financial-sweep`, modelo "Varredura financeira diária (R1)"): agenda → `ton.financial_sweep` → se há caso novo, aviso no TON; ligada/ajustada/pausada pelo chat (`ton_propose_daily_sweep`) com testes, hora e faixas aprovados no clique
- [x] 4.6 Nós de automação: passo `ton.financial_test` (um teste, opcionalmente registra), passo `ton.financial_sweep` (vários testes, um evento por execução) e gatilho `trigger.ledger_cases` (casos registrados pelo chat, R1 ou automação; filtro por teste, criticidade e só novos)
- [x] 4.7 Tela `/ton/ocorrencias`: ledger em tabela (Abertas/Vencidas/Todas, busca), detalhe com evidência, critério de verificação e histórico; rotas `GET /ton/agent/ledger` e `/ledger/{id}`
- [x] 4.8 Base da criticidade: unidade operacional com receita no mês mede na própria receita; não operacional ou em implantação mede no consolidado
- [ ] 4.4 Período e unidade fixados na conversa (seletor no campo de mensagem)
- [ ] 4.5 Sugestões de próximo passo depois de cada resposta

## Onda 5 — Pedidos de 2026-10-23

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`; atas da Controladoria de 16/10 e 20/10.

- [ ] 5.1 Excluir linha da estrutura da DRE (pela tela e pela proposta do chat), com motivo, histórico e voltar versão; a Luyla tentou pelo chat e não conseguiu (hoje só ocultar e tirar do resultado)
- [ ] 5.2 Tirar a contingência de 1% do padrão de "percentual sobre o faturamento" (prompt do TON e descrição da ferramenta); manter taxa de administração, PIS e COFINS até a apuração efetiva substituir os percentuais fixos
- [ ] 5.3 Especialista de calendário anual por unidade (pedido da Luyla): eventos locais (festas, romarias, padroeira) que mudam combustível, gasto, horas extras e necessidade de caixa; aviso antecipado ao gestor (ex.: temporário mais barato que hora extra). Depende de `hr-payroll-domain` (horas extras) e de um calendário mantido pela Controladoria
- [ ] 5.4 Assistente com contexto do gráfico ou registro clicado ("perguntar sobre este indicador"), como no CES (ver `platform-ces-foundation`)
- [ ] 5.5 Chat continua sendo o foco principal: novas necessidades da Luyla chegam pelo grupo e entram como tarefas aqui
