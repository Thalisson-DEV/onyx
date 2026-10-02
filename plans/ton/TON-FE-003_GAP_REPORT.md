# TON-FE-003 — Gap Report

Auditoria feita em 2026-10-02 sobre `a7dc9b9bc2` (main), lendo código, banco local e o
produto em Chrome (`next dev :3005` contra a API local, sessão do usuário autorizado).
Base local = demonstração sintética (julho/2026, 13 bloqueios). Nada abaixo é dado real
da Vale Norte.

Legenda de prioridade: **P0** fecha o loop de decisão; **P1** utilidade diária;
**P2** maturidade. Confiança: alta = verificado em código e no navegador; média =
verificado em código; baixa = hipótese.

---

## 1. Forças atuais (o que já está certo e deve ser reaproveitado)

| Força | Evidência |
|---|---|
| Decisões financeiras já são **versionadas e imutáveis** | `ton_financial_mapping_revision`, `ton_financial_amount_basis_revision`, `ton_financial_reconciliation_decision`, `ton_financial_candidate_decision`, `ton_dre_structure_version` têm `created_by`, `created_at`, `reason` e trigger `ton_financial_immutable` |
| Cada base normalizada registra **quais versões de decisão usou** | `ton_financial_normalization_run.mapping_revision_number`, `amount_basis_revision_number`, `reconciliation_decision_number` |
| Recalcular é **determinístico, idempotente e rápido** | `financial_domain.normalize` usa `input_digest`; mesma entrada devolve a mesma base; ~100 ms na base local |
| Candidatos só com evidência determinística | `financial_readiness._candidate`: código exato ou mapeamento aprovado anterior; rejeição registrada |
| Auditoria por evento | `emit_ton_audit_event` em mapeamento, base, conciliação, rejeição, DRE |
| Fronteira humana já respeitada na UI | diálogo de decisão exige justificativa e confirmação; reconciliação sem escolha padrão |
| Shell TON próprio, copy pt-BR, tokens, primitives | FE-001/FE-002 |
| Modelo de ocorrências com responsável/prazo/eventos | `ton_occurrence`, `_assignment`, `_event`, `_impact`, `_note` (vazio na base local) |

## 2. Fraquezas centrais

1. O loop **decidir → recalcular → ver consequência** está quebrado em três pedaços sem ligação.
2. O usuário decide **sem ver os registros** que está decidindo.
3. Nenhuma superfície responde "o que mudou?" apesar de o banco ter tudo para isso.
4. Fechamento é uma página de leitura; não é um centro de controle.
5. Assistente responde e oferece links genéricos, não a ação específica.

---

## 3. Gaps de workflow

### W1 — Decisão termina em "Decisão registrada" e nada mais (P0, alta)
- **Evidência:** `PendingPage.approve()` só faz `setSaved(true)`. A prontidão vem da base
  normalizada; a decisão só tem efeito depois de `POST /normalizations/{id}/recompute`,
  que fica num botão separado no topo ("Recalcular prontidão"), sem relação com a decisão.
  Depois do recálculo a página só re-renderiza os números — sem antes/depois.
- **Impacto:** o usuário não sabe se a decisão resolveu algo; precisa lembrar números
  anteriores; pode achar que nada aconteceu (a fila continua igual até recalcular).
- **Solução:** após confirmar, recalcular (quem tem permissão) e mostrar o resultado
  determinístico: bloqueios antes → agora por categoria, status da DRE, o que continua
  pendente. Sem permissão de recálculo: estado explícito "registrada, aguardando recálculo".
- **Dependências:** read model de comparação entre bases (B2).

### W2 — Decisões registradas e não aplicadas ficam invisíveis (P0, alta)
- **Evidência:** a base mais recente guarda os números de versão usados; nenhuma API compara
  com a versão corrente. Após refresh, uma decisão salva sem recálculo some da tela.
- **Impacto:** fechamento pode ser publicado/analisado sobre base desatualizada sem ninguém saber.
- **Solução:** expor "N decisões registradas ainda não aplicadas" (comparação de versões) no
  Fechamento, Pendências e fila de trabalho, com a ação "Recalcular".

### W3 — Sem histórico de decisões (P0, alta)
- **Evidência:** FE-002 marcou "trilha de auditoria de decisões" como `[~]` / `[d]` por falta
  de endpoint de leitura. As tabelas existem.
- **Impacto:** "quem decidiu, quando, por quê, qual versão" não é visível — exigência explícita
  do roadmap; sem isso não há confiança para controladoria.
- **Solução:** `GET /api/ton/financial-domain/decisions` (log unificado, legível, sem IDs).

### W4 — Não existe "o que preciso resolver hoje?" (P0, alta)
- **Evidência:** Home tem "atenção" e Pendências tem a fila por categoria; fontes com problema,
  decisões não aplicadas, DRE pronta-mas-não-calculada e ações vencidas não aparecem juntas.
- **Solução:** fila de trabalho unificada (B4), alimentada só por estados persistidos.
  Responsável/prazo apenas quando a ocorrência tiver atribuição (hoje: nenhuma).

### W5 — DRE pode ficar pronta sem cálculo (P1, média)
- **Evidência:** `POST /api/ton/dre/calculations` só é chamado por botão explícito no
  workspace DRE. Após a última decisão, nada sugere "a DRE ficou pronta — calcular".
- **Solução:** quando a comparação mostrar período passando a READY, o resultado da decisão
  e a fila oferecem "Calcular DRE" (ação explícita, não automática).

### W6 — Resolução em lote inexistente (P1, média)
- **Evidência:** cada mapeamento é uma chamada; candidatos `EXACT_CODE` repetidos teriam de ser
  aprovados um a um. Na base local não há candidatos exatos (unidade "001 - Synthetic unit"
  não bate com nenhum código), logo nada demonstrável hoje.
- **Solução:** lote somente para candidatos `EXACT_CODE`/`APPROVED_MAPPING`, com prévia de
  escopo e confirmação explícita. Conciliações nunca em lote (julgamento por item).
- **Decisão:** adiado até existir evidência em dados (D-026).

## 4. Gaps de trust/explicabilidade

### T1 — Conciliação decidida sem valores nem documentos (P0, alta)
- **Evidência:** `list_blockers(SOURCE_RECONCILIATION_*)` devolve só uma string
  `"UNMAPPED; NG yes; billing no; …; amount relation unverified"`. A UI mostra
  "Conta e unidade vinculadas. Documento e valor precisam de conferência." — mas não mostra
  documento nem valor. Os fatos têm `document_number`, `emission_date`, `movement_amount`,
  `invoice_number`, `service_amount`, `payer_text`.
- **Impacto:** o usuário é convidado a classificar uma diferença que não consegue ver; vai
  abrir a planilha fora do TON (workflow gap) ou decidir às cegas (risco de controle).
- **Solução:** projeção segura `records[]` na linha do bloqueio: lado (NG/Faturamento),
  documento, data, competência, conta, unidade de origem, valor, localização (planilha/linha).

### T2 — Unidade/conta sem mapeamento sem amostra dos lançamentos (P0, alta)
- **Evidência:** linha mostra só `"001 - Synthetic unit"` e "2 registros afetados".
- **Solução:** mesma projeção `records[]` (até 5 lançamentos por chave).

### T3 — "Impacto da decisão" é genérico (P0, alta)
- **Evidência:** `COPY.pending.dialog.consequence(record_count)` — uma frase fixa.
- **Solução:** prévia determinística do que a decisão altera (que fato muda, quantos registros,
  quais períodos) + resultado real após recálculo (W1). Nenhuma previsão inventada.

### T4 — "Leitura do TON" no Fechamento repete o status (P1, alta)
- **Evidência:** SITUAÇÃO/IMPACTO/CAUSA/PRÓXIMA AÇÃO repete o cartão superior com frases
  genéricas ("Não quantificado. Nenhum valor financeiro foi estimado.").
- **Solução:** substituir por "O que mudou" e "Decisões recentes" (fatos persistidos).

## 5. Gaps de automação / follow-up

### A1 — Sem recálculo pós-decisão (P0, alta) → resolvido por W1.
### A2 — Eventos de decisão e mudança de prontidão fora das notificações (P1, alta)
- **Evidência:** `lib/ton/activity.ts` deriva só de relatórios, importações e especialistas;
  FE-002 adiou "DRE state events" e "decision events".
- **Solução:** derivar do log de decisões e da comparação entre bases (sem polling novo).
### A3 — R3 não sabe que algo mudou (P1, média)
- **Evidência:** R3 roda por agenda; não há regeneração "quando o estado muda". Gerar relatório a
  cada decisão seria ruído.
- **Solução:** mostrar no Fechamento "último relatório é anterior às decisões X" e oferecer
  gerar novamente (explícito). Automático fica para quando houver política aprovada.
### A4 — Lembretes com prazo (P2, alta)
- **Evidência:** prazos só existem em `ton_occurrence_assignment` (0 linhas). Sem prazo real,
  lembrete seria inventado. Bloqueado por dados.

## 6. Gaps do assistente ↔ produto

### C1 — Continuações genéricas (P0, alta)
- **Evidência:** `TonExecutionSummary` empilha links fixos ("Ver pendências", "Abrir DRE")
  conforme a família de ferramenta usada. Os dados de prontidão retornados pela ferramenta
  (bloqueios por código e período) são ignorados.
- **Solução:** CTAs específicos derivados do resultado da ferramenta: "Resolver 3 conciliações"
  → `/ton/pendencias?blocker=SOURCE_RECONCILIATION_UNRESOLVED&period=…`.
### C2 — TON não responde "o que mudou depois das decisões?" (P0, alta)
- **Evidência:** nenhuma ferramenta lê versões de decisão ou compara bases.
- **Solução:** ferramenta `ton_get_recent_changes` sobre os mesmos read models (B2/B3).

## 7. Gaps de dados/integração (bloqueadores reais — não implementar com dado inventado)

| Gap | Estado | Depende de |
|---|---|---|
| NG/Keevo direto | importação manual | VPN/API/DB read-only, autorização |
| Dados reais aprovados | só sintético local | amostra aprovada Vale Norte |
| Responsável/prazo de pendências | inexistente no domínio de prontidão | definição de donos pela Controladoria (Luyla) |
| Histórico 2025+ | inexistente | acesso ao histórico — sem isso não há anomalia/sazonalidade |
| Frescor de fonte com SLA | só "última importação" | periodicidade oficial por fonte; não inventar limite de dias |
| Domínios operacionais | sem fonte | frota, contratos, compras, RH, compliance |

## 8. Gaps de UX / apresentação

| # | Gap | Prioridade |
|---|---|---|
| U1 | `PendingPage` com 1.254 linhas; diálogo mistura 6 tipos de decisão — difícil evoluir | P0 (refatorar junto com W1) |
| U2 | Status "Sem decisão" repetido em toda linha (redundante na fila de pendências) | P1 |
| U3 | Linha de dotação mostra UUID como chave (`source_key` = execution id) e "períodos" vazio | P1 |
| U4 | "Opções avançadas" expõe `rev. 8` e várias bases idênticas por data | P1 |
| U5 | Fechamento: cartões de categoria + leitura + especialistas + fontes, nenhum "próximo passo" ordenado | P0 |
| U6 | Notificações sem decisões | P1 |

## 9. Proatividade suportada por dados (o que é real hoje)

| Sinal | Suportado? | Base |
|---|---|---|
| Bloqueios resolvidos/novos entre bases | **sim** | comparação determinística de prontidão entre bases |
| Decisões não aplicadas | **sim** | números de versão |
| Fonte com falha de importação | **sim** | `data-sources.status` |
| Fonte "desatualizada" | parcial | só data da última importação; sem SLA → mostrar data, não julgar |
| Correções repetidas | parcial | `ton_occurrence_event` suporta repetição; 0 ocorrências locais |
| Anomalias financeiras | **não** | sem histórico; não ativar |

## 10. Plano priorizado

**P0 (este sprint):**
- B1 evidência de registros nas linhas de bloqueio (T1, T2)
- B2 comparação entre bases + decisões não aplicadas (W1, W2)
- B3 log de decisões (W3)
- F1 diálogo de decisão: evidência → decisão → prévia → confirmação → registro → recálculo →
  antes/depois (W1, T3), com refatoração do PendingPage (U1)
- F2 Fechamento como centro de controle (U5, T4, W2, A3)
- F3 fila de trabalho unificada (W4)
- F4 CTAs específicos no assistente + ferramenta "o que mudou" (C1, C2)

**P1:** notificações de decisão/prontidão (A2), DRE pronta → calcular (W5), lote seguro (W6),
U2–U4, frescor de fonte honesto.

**P2:** lembretes por prazo (A4, bloqueado por dados), admin de automações, personalização.

## 11. Referências externas

Padrões consultados por conhecimento de produto (não copiados): fila de exceções de
conciliação (BlackLine/FloQast — "itens abertos com evidência lado a lado"), trilha de
auditoria por decisão (Workiva), checklist de fechamento com dependências (FloQast close
checklist). Aproveitado: evidência lado a lado na conciliação; "antes/agora" após ação;
estado "aguardando recálculo" explícito.
