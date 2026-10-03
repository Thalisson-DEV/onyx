# TON — GAPS ATUAIS E OPORTUNIDADES DE PRODUTO

Este documento combina problemas já observados com hipóteses de evolução. O agente deve validar no código antes de implementar.

---

# 1. GAP CRÍTICO — loop de decisão

Hoje o TON consegue detectar/exibir bloqueio.

O macro gap é fechar:

```text
finding
→ evidence
→ human decision
→ recompute
→ visible consequence
→ verification later
```

Este deve ser o próximo grande salto.

---

# 2. GAP — “o que preciso fazer hoje?”

O produto precisa de uma fila unificada capaz de responder:

- o que mudou;
- o que está bloqueado;
- o que precisa da minha decisão;
- o que está atrasado;
- o que o TON pode fazer agora.

---

# 3. GAP — detecção sem follow-up

TON pode encontrar algo e parar.

Evoluir para:
- follow-up;
- reminder;
- recompute;
- notify;
- re-check;
- closure verification.

---

# 4. GAP — “o que mudou?”

Um recurso de alto valor seria:

`O que mudou desde a última análise?`

Mas precisa usar versões persistidas e dados reais.

---

# 5. GAP — repetição de trabalho financeiro

O agente deve procurar tarefas ainda feitas fora do TON:

- montagem manual de fechamento;
- copiar informações;
- reconciliação;
- verificação de source freshness;
- comparação de mês;
- cobrança de pendências;
- geração repetida de relatórios;
- explicações para diretoria.

Priorizar pelo impacto real.

---

# 6. GAP — confiança

Cada conclusão precisa deixar claro:

- fato;
- origem;
- certeza;
- hipótese;
- consequência;
- próxima ação.

Sem transformar a interface em uma tela técnica.

---

# 7. GAP — especialista como inteligência contextual

Hoje a página “Especialistas” pode ser menos importante do que mostrar:

```text
Última análise:
AUDITOR → validou base
CFO → identificou 3 pendências
CEO → consolidou
```

Especialistas devem parecer inteligência trabalhando, não um catálogo de bots.

---

# 8. GAP — autonomia verdadeira

R3 é foundation.

Próximas oportunidades:
- recompute after decisions;
- detect state changes;
- publish meaningful reports;
- action reminders;
- R9 verification;
- R5 Dinheiro Escondido;
- source freshness.

Autonomia não é executar jobs.
É fechar ciclos.

---

# 9. GAP — source integration

A maior fonte de valor potencial do TON continua sendo reduzir o intervalo:

```text
manual export
→ manual upload
→ analysis
```

para:

```text
NG/VPN/API/DB
→ ingestion
→ analysis
```

Depois:
near real-time / schedule.

---

# 10. GAP — historical learning

O Prompt Mestre pede previsão e comparação histórica.

Sem histórico suficiente, não ativar:
- robust anomaly detection;
- forecasting;
- seasonality conclusions.

Ideal:
history 2025+.

---

# 11. GAP — ROI

O Prompt Mestre quer:
- economia potencial;
- economia realizada;
- receita recuperada;
- custo evitado;
- ROI.

Mas sem verification loop isso vira promessa.

Primeiro:
detecção + owner + deadline + verification.

Depois:
ROI.

---

# 12. GAP — operations beyond finance

Os seguintes domínios precisam de fontes:

- Frota;
- Produção;
- Contratos;
- RH;
- Compras;
- Compliance.

A arquitetura já foi desenhada para crescer por domínio.

---

# 13. O que NÃO deve ser prioridade agora

- novas páginas sem workflow;
- dashboards decorativos;
- mais indicadores sintéticos;
- chatbot “mágico”;
- generic AI features;
- social/channel integrations sem contrato;
- fancy animations.

Primeiro valor operacional.

---

# 14. Atualização 2026-10-02 — o gap principal mudou

Gaps 1–4 e 7 deste documento foram resolvidos no FE-003 (loop de decisão, fila diária, "o que
mudou", especialistas na timeline). Os gaps que importam agora são os do **Prompt Mestre**, não de UX:

1. Contrato de dados e níveis de confiança (§3).
2. Protocolo de 7 passos com bloqueio e pontos cegos (§5, §11).
3. Sanidade S1–S9 e testes T1–T30 (§6–§8) — hoje só S10 e T4 parcial.
4. Quantificação em R$, régua PAD-CTRL-001 e escalonamento (§9, §10).
5. Ledger operado com dono, prazo e verificação no ciclo seguinte; ROI (§13).
6. Cadastro mestre do contrato e margem prevista × real (§4) — o "cérebro" inexistente.
7. Domínios operacionais e 6 especialistas sem fonte (§15); integração Zeev a concluir.
8. Rotinas autônomas R1–R9 (§12) — só R3.

Cada um virou change em `openspec/changes/`, ordenada em `openspec/roadmap.md`.
