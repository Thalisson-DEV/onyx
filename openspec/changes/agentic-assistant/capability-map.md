# Mapa de capacidades do agente TON

Fonte: regras de negócio do código atual, Prompt Mestre (digesto `plans/ton/context/02`),
processo e problemas da Controladoria (`plans/ton/context/03`), gaps (`plans/ton/context/09`) e
atas de 03/10 a 20/10/2026. Cada linha diz o que o agente faz, como, e se o serviço já existe.

## Níveis de autonomia (Prompt Mestre §12)

| Nível | O que é | Exemplo | Como no chat |
|---|---|---|---|
| **Livre** | Ler, testar, calcular, comparar, redigir | rodar T3 duplicidade, comparar Mossoró jan × set | ferramenta de leitura; cartão de resultado |
| **Registro** | Escrever no ledger sem mudar número oficial | registrar ocorrência, anotar evidência, lembrar regra | proposta com clique (fase 1); livre depois que a Controladoria aprovar a regra |
| **Decisão** | Muda base, DRE, decisão ou responsável | tratamento, estrutura, classificação, importação, decisão de pendência | proposta com Aplicar / Cancelar / Desfazer |
| **Proibido** | Prompt Mestre §2 | escrever no NG, alterar faturamento, falar com contratante, encerrar crítica, acusar pessoa | recusa e diz quem decide |

## 1. Fontes e importação

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Situação das fontes, última importação, diagnósticos | Livre | `ton_list_sources` ✅ | — |
| Importar arquivo anexado como nova versão da fonte, com prévia de reimportação | Decisão | `client_import.preview/upload` ✅ → `ton_propose_source_import` ✅ | 1 |
| Ver linhas rejeitadas e por quê | Livre | `get_problem_rows` ✅ → ferramenta nova | 2 |
| Colar tabela corrigida no chat (linhas problemáticas) e reimportar | Decisão | `paste_client_table` ✅ | 3 |
| Detectar fonte atrasada pelo POP (NG até dia X, PIS/COFINS dia 5) | Livre | novo (calendário do POP) | 4 |

## 2. Classificação de contas (natureza)

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Listar contas sem natureza e as sugestões da IA | Livre | `classification_table` ✅ | 2 |
| Classificar conta / confirmar sugestões em lote | Decisão | `change_classification`, `confirm_batch` ✅ | 2 |
| Criar natureza nova (com grupo da DRE) | Decisão | `create_nature` ✅ | 2 |
| Regra de fornecedor → natureza (ata 16/10) | Decisão | novo (change `supplier-nature-consistency`) | 3 |

## 3. Revisão do NG e pendências

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Listar e explicar pendências com evidência | Livre | `ton_list_findings`, `ton_get_finding` ✅ | — |
| Decidir pendência (aceitar, excluir, corrigir na fonte…) com justificativa | Decisão | `record_decision` ✅ | 2 |
| Atribuir unidade a lançamento sem unidade, em lote | Decisão | `assign_unit__no_commit` ✅ | 2 |
| Sugerir a unidade pelo histórico (mesmo fornecedor/conta) | Livre | novo | 2 |

## 4. Tratamentos de fechamento

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Excluir, reclassificar, substituir por fonte | Decisão | `create_treatment` ✅ → `ton_propose_closing_treatment` ✅ | 1 |
| Listar tratamentos em vigor e histórico | Livre | `treatment_table` ✅ | 2 |

## 5. DRE

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Estrutura: criar/renomear/mover/ocultar/tirar do resultado, mover natureza | Decisão | versões ✅ → `ton_propose_dre_structure_change` ✅ | 1 |
| Faturamento bruto, retenções, ISS da nota como linhas | Decisão | origem `BILLING` ✅ | 1 |
| Ajuste da Controladoria por mês e unidade (PIS/COFINS enquanto a planilha não chega) | Decisão | origem `ADJUSTMENT` ✅ | 1 |
| Recalcular mês/ano, consolidado e unidades | Decisão | `execute_year` ✅ | 1 |
| Lançamentos de uma linha (drill-down) | Livre | `list_contributors` ✅ → ferramenta | 2 |
| Comparar meses, unidades, acumulado; ranking de variações | Livre | `get_year`, `get_units_year` ✅ → ferramenta | 2 |
| Exportar o Excel da DRE (link no chat) | Livre | `export_workbook` ✅ | 2 |
| Voltar versão da estrutura | Decisão | `restore_version` ✅ | 2 |

## 6. Investigação (testes do Prompt Mestre sobre dados reais)

Todos rodam sob demanda, com parâmetros explícitos na resposta ("parâmetro do teste, não regra
aprovada") e evidência com planilha e linha. Nenhum vira regra ativa sem aprovação.

| Teste | O que procura | Dados | Onda |
|---|---|---|---|
| T1 Grupo zerado | linha da DRE zerada no mês com valor nos 3 meses anteriores | DRE calculada | 2 |
| T2 Desvio de média | natureza × unidade fora da média móvel de 3 meses | NG | 2 |
| T3 Duplicidade | mesmo documento e valor em fornecedores distintos; mesmo fornecedor, valor e data | NG | 2 |
| T4 Receita NF × NG | faturamento líquido × receita do NG por unidade e mês | NG + faturamento | 2 |
| T6 Sinal invertido | receita negativa ou custo positivo | NG + estrutura | 2 |
| T8 Fornecedor × unidade | fornecedor novo na unidade ou pago por muitas unidades | NG (histórico) | 2 |
| T9 Competência retroativa | "COMP. MM/AAAA" do histórico ≠ mês do lançamento | NG | 2 |
| T10 Não recorrente | lançamento acima de N× a mediana da natureza | NG | 2 |
| Busca livre | fornecedor, histórico, documento, valor, natureza, unidade, período | NG | 2 |
| Resumo por fornecedor | maiores fornecedores por natureza/unidade e variação | NG | 2 |
| T5, T7, T11, T12 | receita replicada, pagamento sem apropriação, partes relacionadas, rescisão | dependem de cadastro | 4 |
| T13–T30 | operação, contrato, frota, RH, compras | dependem das fontes dos domínios | 5 |

## 7. Ledger de ocorrências e oportunidades

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Registrar ocorrência a partir de um teste, com evidência e criticidade PAD-CTRL | Registro | ✅ `ton_propose_ledger_registration` (regras `TON-T*`) | 4 |
| Atribuir responsável e prazo | Decisão | ✅ `ton_propose_occurrence_assignment` | 4 |
| Anotar nota/evidência | Registro | ✅ `ton_propose_occurrence_assignment` | 4 |
| Registrar impacto e verificar no ciclo seguinte (ROI) | Registro | `record_impact`, `verify_impact` ✅ | 4 |
| Ações vencidas, o que fazer hoje | Livre | `ton_list_overdue_actions` ✅ + fila | 2 |

## 8. Comunicação, relatórios e rotinas

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Publicar relatório de fechamento / resumo executivo | Decisão | ✅ | — |
| Criar e ajustar automação (rascunho) | Livre | ✅ | — |
| Ativar, pausar, rodar agora, ver execuções | Decisão | `set_status`, run ✅ | 2 |
| E-mail interno de inconsistências (ata 03/10) | Decisão | automação de e-mail ✅ | 2 |
| Rodar R3 (fechamento preliminar) agora / agendar | Decisão | rotas R3 ✅ | 2 |

## 9. Memória da Controladoria

| Capacidade | Tipo | Serviço | Onda |
|---|---|---|---|
| Lembrar regra dita na conversa ("parcelamento fica fora") | Registro | novo `ton_controller_rule` | 3 |
| Ler regras e decisões passadas antes de responder | Livre | novo + `decision_log` ✅ | 3 |

## 10. Especialistas

Cada especialista tem conversa própria com ferramentas do seu domínio:

| Especialista | Foco | Ferramentas principais |
|---|---|---|
| CFO | DRE, receita, impostos, margem, tratamentos | DRE, ajustes, estrutura, T1, T2, T4, T6, T10 |
| AUDITOR | base, pendências, evidência, duplicidade | fontes, revisão, T3, T8, T9, decisões, unidade |
| CEO | resumo em 5 linhas, relatórios | visão geral, relatórios, ocorrências |
| CONTRATOS, FROTA, RH, COMPRAS, COMPLIANCE, COO | aguardam fonte | só leituras; dizem o que falta |

## 11. Proatividade (fase seguinte)

- ✅ Varredura diária (R1) rodando os testes da seção 6 e registrando ocorrências (`ton_propose_daily_sweep`).
- Abrir conversa sozinho quando uma importação nova muda a DRE ou cria bloqueio.
- Lembrar prazos do POP e ações vencidas (R9).
