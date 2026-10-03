# TON — ARQUITETURA ATUAL E MODELO DE EXECUÇÃO

## 1. Plataforma

Base tecnológica do produto mantém a maturidade do Onyx:

- Python backend;
- Next.js/React frontend;
- autenticação;
- RBAC;
- conversas;
- streaming;
- LLM providers;
- tool calling;
- arquivos;
- RAG;
- Code Interpreter;
- web search;
- artifacts;
- workers;
- connectors;
- scheduler/queue;
- audit.

A stack original foi mantida deliberadamente.

---

# 2. TON Coordinator

Conceito atual:

**TON é o principal agente/Persona visível ao usuário.**

Ele:
- conversa;
- usa tools;
- coordena especialistas;
- analisa;
- gera evidência/relatórios;
- navega entre workflows;
- sintetiza respostas.

O runtime de conversa é reaproveitado do Onyx.

---

# 3. Especialistas

Os especialistas canônicos são:

- CFO
- COO
- FROTA
- CONTRATOS
- COMPLIANCE
- PROCUREMENT
- RH
- AUDITOR
- CEO

Decisão atual:
eles são **papéis internos do runtime/orquestração TON**, não necessariamente nove Personas independentes do Onyx.

Isso resolve o risco de:
- nove chats desconexos;
- prompts arbitrariamente editáveis;
- duplicação de runtime;
- perda de governança.

Mas esta decisão deve continuar sendo verificada contra o código atual.

Se o runtime existente do Onyx fornecer uma primitiva melhor sem criar duplicação, o agente pode adaptar a arquitetura.

---

# 4. Especialistas como contexto

A interação ideal:

```text
TON
→ foco CFO
→ pergunta
→ TON Coordinator com specialist context
```

Não:

```text
CFO chatbot independente
```

Ao selecionar um especialista, o contexto deve controlar:
- domínio;
- foco;
- ferramentas;
- instruções;
- saída esperada.

Não pode burlar:
- RBAC;
- domínio;
- segurança;
- regras financeiras.

---

# 5. Tools atuais conhecidos

O runtime TON chegou a ter ferramentas como:

### Fontes
- `ton_list_sources`
- `ton_get_source_status`

### Financeiro
- `ton_get_financial_context`
- `ton_get_financial_review_summary`
- `ton_list_findings`
- `ton_get_finding`
- `ton_get_dre_readiness`
- `ton_get_dre_result`
- `ton_get_readiness_evidence`

### Análise
- `ton_analyze_closing`
- `ton_get_billing_summary`
- `ton_get_budget_summary`
- `ton_get_reconciliation_summary`

### Ações
- `ton_list_occurrences`
- `ton_get_occurrence`
- `ton_list_overdue_actions`

### Publicação
- `ton_generate_closing_report`
- `ton_generate_executive_brief`

O agente deve consultar o registro atual dessas tools no código; não assumir que esta lista continua idêntica.

---

# 6. Routines

O Prompt Mestre define R1–R9.

As rotinas são:

R1 — Varredura de exceções
R2 — Auditoria de combustível
R3 — Fechamento preliminar
R4 — Reconciliação contratual
R5 — Painel Dinheiro Escondido
R6 — Pacote executivo
R7 — Sentinela de vigência/reajuste
R8 — Sentinela de recebimento
R9 — Verificação de ações

O código atual já possui fundação de scheduler e R3.

R3 é a rotina flagship atual.

---

# 7. R3

Conceito:

Fechamento preliminar mensal.

Última configuração conhecida:
- mensal;
- primeiro dia útil;
- 08:00 Brasília;
- calendário de Petrolina.

A rotina pode ser executada manualmente e também é agendada.

Ela registra resultado persistido e passos internos.

Na UX:
21 passos internos não devem dominar a tela.

---

# 8. DRE/readiness

O DRE engine não está “sempre pronto”.

Ele deve ser READY somente quando os pré-requisitos financeiros estiverem satisfeitos.

A UI não pode converter NOT_READY em READY por maquiagem.

---

# 9. Sources

Fontes são primeira classe.

Atualmente:
- NG/Keevo: aquisição manual por arquivo;
- Faturamento: arquivo/manual;
- Dotação: arquivo/manual;
- outras integrações dependem de acesso/capability.

NG direto ainda depende de:
- VPN/API ou banco/view read-only;
- documentação;
- autorização.

---

# 10. Administração

Separar mentalmente:

```text
TON PRODUCT
→ Administração do TON

SYSTEM
→ administração técnica do Onyx
```

Admin técnico pode continuar expondo:
- agents/personas;
- models/providers;
- MCP/OpenAPI;
- connectors;
- diagnostics.

Usuário de Controladoria não deve precisar disso.

---

# 11. Frontend atual

Após rebuild FE-001, o TON passou a ter shell próprio:

- Vale Norte;
- TON;
- navigation própria;
- Home;
- Assistant;
- Closing;
- DRE;
- Pendências;
- Automações;
- Relatórios;
- Fontes;
- Especialistas/contexto.

Essa camada nova usa o backend e infraestrutura existentes.

---

# 12. Regra de backend/frontend

Frontend não é fonte de verdade para:
- statuses;
- blockers;
- specialist availability;
- routine schedule;
- mapping;
- DRE calculations.

Frontend apresenta.

Backend/domain decide.

Se faltar um read model adequado:
criar o menor endpoint read-only necessário.

---

# 13. Segurança

Nunca:
- logar credenciais;
- commitar source artifacts do cliente;
- colocar real financial payload em fixture;
- expor raw FileStore refs;
- permitir arbitrary SQL;
- escrever no NG;
- contornar tenant isolation;
- contornar human approvals.

---

# 14. Atualização 2026-10-02 (verificada no código)

- Ferramentas registradas do assistente (19): `ton_list_sources`, `ton_get_source_status`,
  `ton_get_financial_context`, `ton_get_financial_review_summary`, `ton_list_findings`,
  `ton_get_finding`, `ton_get_dre_readiness`, `ton_get_dre_result`, `ton_get_readiness_evidence`,
  `ton_analyze_closing`, `ton_get_billing_summary`, `ton_get_budget_summary`,
  `ton_get_reconciliation_summary`, `ton_list_occurrences`, `ton_get_occurrence`,
  `ton_list_overdue_actions`, `ton_get_recent_changes`, `ton_generate_closing_report`,
  `ton_generate_executive_brief`. Code Interpreter (`run_python`) disponível com limites (D-032).
- Especialistas: definidos em `backend/onyx/ton/agent/registry.py`; CFO, AUDITOR e CEO com
  ferramentas; os outros seis sem ferramentas ("aguardando fonte").
- Cobertura do Prompt Mestre: `backend/onyx/ton/agent/capabilities.py` — S10 operacional, T4 parcial,
  demais S/T não implementados. Rotinas R1–R9 em `registry.ROUTINES`; só R3 executa.
- Ledger: modelo completo em `backend/onyx/db/ton/models.py` (`Occurrence`, `OccurrenceImpact`,
  `OccurrenceAssignment`…); só a revisão NG grava ocorrências.
- Zeev: `backend/onyx/ton/zeev/` — cliente somente leitura com firewall de mutação e catálogo
  (BE-004A/B). Sem sincronização para `SourceSnapshot`.
- Arquitetura-alvo das próximas camadas (protocolo de 7 passos, baterias S/T, cadastro mestre,
  framework de rotinas, subagentes, Zeev): `openspec/changes/*/design.md`.
